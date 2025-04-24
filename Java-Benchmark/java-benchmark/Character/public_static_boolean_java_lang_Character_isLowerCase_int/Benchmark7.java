

public class Benchmark7 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Boolean output_1 = Character.isLowerCase(input_1_0);
        Boolean output_2 = Character.isLowerCase(input_2_0);

        
        // Compare output
        if (output_1 == true && output_2 == false) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

