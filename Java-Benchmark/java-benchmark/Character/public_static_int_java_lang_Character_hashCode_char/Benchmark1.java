

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Character input_2_0 = args[1].charAt(0);


        // Perform computation         
        Integer output_1 = Character.hashCode(input_1_0);
        Integer output_2 = Character.hashCode(input_2_0);

        
        // Compare output
        if (output_1 == 32 && output_2 == 122) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

