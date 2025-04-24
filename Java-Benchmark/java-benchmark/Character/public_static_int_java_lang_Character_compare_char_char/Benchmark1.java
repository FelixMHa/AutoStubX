

public class Benchmark1 {
    public static void main(String[] args) {
        // fetch input
        Character input_1_0 = args[0].charAt(0);
        Character input_1_1 = args[1].charAt(0);
        Character input_2_0 = args[2].charAt(0);
        Character input_2_1 = args[3].charAt(0);


        // Perform computation         
        Integer output_1 = Character.compare(input_1_0, input_1_1);
        Integer output_2 = Character.compare(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == 66 && output_2 == -38) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

